#
# Signal Protocol Python library
# signal/message.py - message handling class
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
Exception base class and implementations.
'''

import base64
import enum


class PushMessageContent(object):
    '''
    '''

    class AttachmentPointer(object):
        '''
        '''

        def __init__(self, attachment_id, content_type, key):
            '''
            '''

            self.id = attachment_id
            self.content_type = content_type
            self.key = key


    class GroupContext(object):
        '''
        '''

        class Type(enum.Enum):
            '''
            '''

            UNKNOWN = 0
            UPDATE = 1
            DELIVER = 2
            QUIT = 3


        def __init__(self):
            '''
            '''

            self.id = # bytes
            self.type = # GroupContext.Type
            self.name = # string
            self.members = []
            self.avatar = # AttachmentPointer


    class Flags(enum.Enum):
        '''
        '''

        END_SESSION = 1


    def __init__(self, body=None, attachments=None, groups=None, flags=None):
        '''
        '''

        self.body = body

        if attachments is not None:
            self.attachments = (AttachmentPointer(att) for att in attachments)
        else:
            self.attachments = tuple()

        if groups is not None:
            self.groups = (GroupContext(gro) for gro in groups)
        else:
            self.groups = tuple()

        self.flags = flags


    def to_base64(self):
        '''
        '''

        data = bytearray()

        if self.body is not None:
            data.extend(bytes(self.body))

        for attachment in self.attachments:
            data.extend(attachment.to_bytes())

        for group in self.groups:
            data.extend(group.to_bytes())

        if self.flags is not None:
            data.append(bytes(self.flags.value))

        return base64.b64encode(data)


# def from_base64(b64_data):
#    '''
#    '''
#
#    data = base64.b64decode(b64_data)
#    data_length = len(data)
#
#    i = 0
#
#    body_length = None
#    while i < data_length:
#        i += 1 # Increment before check, to make sure i gets past NULL character.
#        if data[i-1] == "\0":
#            body_length = i-1
#            break
#
#    body = str(data[0:body_length]) if body_length is not None else None
