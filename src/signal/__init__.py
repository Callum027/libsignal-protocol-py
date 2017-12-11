#
# Signal Protocol Python library
# __init__.py - library public classes and methods
#
# Copyright (c) 2017 Catalyst.net Ltd
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


'''
'''


import threading

import requests


class Signal(object):
    '''
    '''


    def __init__(self, number, endpoint=):
        '''
        '''

        self.number = number
        self.endpoint = endpoint

        self.lock = threading.Lock()


    def send(self, username, message, verify_receipt=False):
        '''
        '''

        self.lock.acquire(blocking=verify_receipt)

        

        self.lock.release()


    def receive(self, callback):
        '''
        '''

        self.lock.acquire(blocking=True)

        

        self.lock.release()


    def attachment_allocate(self, data):
        '''
        '''

        pass


    def attachment_retrieve(self, attachment_id):
        '''
        '''

        pass
