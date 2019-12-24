
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2015 clowwindy
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


# we clear at most TIMEOUTS_CLEAN_SIZE timeouts each time
import logging
import errno
import sys
sys.path.append('..')
from cnp import eventloop



# for each handler, we have 2 stream directions:
#    upstream:    from client to server direction
#                 read local and write to remote
#    downstream:  from server to client direction
#                 read remote and write to local

STREAM_UP = 0
STREAM_DOWN = 1

# for each stream, it's waiting for reading, or writing, or both
WAIT_STATUS_INIT = 0
WAIT_STATUS_READING = 1
WAIT_STATUS_WRITING = 2
WAIT_STATUS_READWRITING = WAIT_STATUS_READING | WAIT_STATUS_WRITING

BUF_SIZE = 32 * 1024
class TCPRelay(object):
    def __init__(self,  local_sock, remote_sock, loop):
        self._local_sock = local_sock
        self._remote_sock = remote_sock
        self._loop = loop
        self._data_to_write_to_local = []
        self._data_to_write_to_remote = []
        self._upstream_status = WAIT_STATUS_READING
        self._downstream_status = WAIT_STATUS_READING
        loop.add(local_sock , eventloop.POLL_IN | eventloop.POLL_ERR, self)
        loop.add(remote_sock , eventloop.POLL_IN | eventloop.POLL_ERR, self)
        self._is_destroted = False

    def _update_stream(self, stream, status):
        # update a stream to a new waiting status
        # check if status is changed
        # only update if dirty
        dirty = False
        if stream == STREAM_DOWN:
            if self._downstream_status != status:
                self._downstream_status = status
                dirty = True
        elif stream == STREAM_UP:
            if self._upstream_status != status:
                self._upstream_status = status
                dirty = True
        if not dirty:
            return

        if self._local_sock:
            event = eventloop.POLL_ERR
            if self._downstream_status & WAIT_STATUS_WRITING:
                event |= eventloop.POLL_OUT
            if self._upstream_status & WAIT_STATUS_READING:
                event |= eventloop.POLL_IN
            self._loop.modify(self._local_sock, event)
        if self._remote_sock:
            event = eventloop.POLL_ERR
            if self._downstream_status & WAIT_STATUS_READING:
                event |= eventloop.POLL_IN
            if self._upstream_status & WAIT_STATUS_WRITING:
                event |= eventloop.POLL_OUT
            self._loop.modify(self._remote_sock, event)

    def _write_to_sock(self, data, sock):
        # write data to sock
        # if only some of the data are written, put remaining in the buffer
        # and update the stream to wait for writing
        if not data or not sock:
            return False
        uncomplete = False
        try:
            l = len(data)
            s = sock.send(data)
            if s < l:
                data = data[s:]
                uncomplete = True
        except (OSError, IOError) as e:
            error_no = eventloop.errno_from_exception(e)
            if error_no in (errno.EAGAIN, errno.EINPROGRESS,
                            errno.EWOULDBLOCK):
                uncomplete = True
            else:
                logging.error(e)
                self.destroy()
                return False
        if uncomplete:
            if sock == self._local_sock:
                self._data_to_write_to_local.append(data)
                self._update_stream(STREAM_DOWN, WAIT_STATUS_WRITING)
            elif sock == self._remote_sock:
                self._data_to_write_to_remote.append(data)
                self._update_stream(STREAM_UP, WAIT_STATUS_WRITING)
            else:
                logging.error('write_all_to_sock:unknown socket')
        else:
            if sock == self._local_sock:
                self._update_stream(STREAM_DOWN, WAIT_STATUS_READING)
            elif sock == self._remote_sock:
                self._update_stream(STREAM_UP, WAIT_STATUS_READING)
            else:
                logging.error('write_all_to_sock:unknown socket')
        return True


    def _write_to_sock_remote(self, data):
        self._write_to_sock(data, self._remote_sock)


    def _on_local_read(self):
        # handle all local read events and dispatch them to methods for
        # each stage
        if not self._local_sock:
            return
        data = None
        buf_size = BUF_SIZE
        try:
            data = self._local_sock.recv(buf_size)
        except (OSError, IOError) as e:
            if eventloop.errno_from_exception(e) in  (errno.ETIMEDOUT, errno.EAGAIN, errno.EWOULDBLOCK):
                return
        if not data:
            self.destroy()
        self._write_to_sock(data,self._remote_sock)
        return

    def _on_remote_read(self):
        # handle all remote read events
        data = None
        buf_size = BUF_SIZE
        try:
            data = self._remote_sock.recv(buf_size)
        except (OSError, IOError) as e:
            if eventloop.errno_from_exception(e) in  (errno.ETIMEDOUT, errno.EAGAIN, errno.EWOULDBLOCK):
                return
        if not data:
            self.destroy()
        self._write_to_sock(data,self._local_sock)
        return

    def _on_local_write(self):
        # handle local writable event
        if self._data_to_write_to_local:
            data = b''.join(self._data_to_write_to_local)
            self._data_to_write_to_local = []
            self._write_to_sock(data, self._local_sock)
        else:
            self._update_stream(STREAM_DOWN, WAIT_STATUS_READING)

    def _on_remote_write(self):
        # handle remote writable event
        if self._data_to_write_to_remote:
            data = b''.join(self._data_to_write_to_remote)
            self._data_to_write_to_remote = []
            self._write_to_sock(data, self._remote_sock)
        else:
            self._update_stream(STREAM_UP, WAIT_STATUS_READING)

    def _on_local_error(self):
        logging.debug('got local error')
        if self._local_sock:
            logging.error(eventloop.get_sock_error(self._local_sock))
        self.destroy()

    def _on_remote_error(self):
        logging.debug('got remote error')
        if self._remote_sock:
            logging.error(eventloop.get_sock_error(self._remote_sock))
        self.destroy()

    def handle_event(self, sock,fd, event):
        # handle all events in this handler and dispatch them to methods
        if self._is_destroted:
            logging.debug('ignore handle_event: destroyed')
            return
        # order is important
        if sock == self._remote_sock:
            if event & eventloop.POLL_ERR:
                self._on_remote_error()
                if self._is_destroted :
                    return
            if event & (eventloop.POLL_IN | eventloop.POLL_HUP):
                self._on_remote_read()
                if self._is_destroted:
                    return
            if event & eventloop.POLL_OUT:
                self._on_remote_write()
        elif sock == self._local_sock:
            if event & eventloop.POLL_ERR:
                self._on_local_error()
                if self._is_destroted:
                    return
            if event & (eventloop.POLL_IN | eventloop.POLL_HUP):
                self._on_local_read()
                if self._is_destroted:
                    return
            if event & eventloop.POLL_OUT:
                self._on_local_write()
        else:
            logging.warn('unknown socket')

    def destroy(self):
        # destroy the handler and release any resources
        # promises:
        # 1. destroy won't make another destroy() call inside
        # 2. destroy releases resources so it prevents future call to destroy
        # 3. destroy won't raise any exceptions
        # if any of the promises are broken, it indicates a bug has been
        # introduced! mostly likely memory leaks, etc
        if self._is_destroted:
            # this couldn't happen
            logging.debug('already destroyed')
            return
        self._is_destroted = True
        if self._remote_sock:
            logging.debug('destroying remote')
            self._loop.remove(self._remote_sock)
            self._remote_sock.close()
            self._remote_sock = None
        if self._local_sock:
            logging.debug('destroying local')
            self._loop.remove(self._local_sock)
            self._local_sock.close()
            self._local_sock = None




    
