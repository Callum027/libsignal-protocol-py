#
# Signal Protocol Python library
# pysignal/exception.py - exception classes
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
Exception classes.
'''


class SignalException(Exception):
    pass


class SignalCLIError(SignalException):
    '''
    '''

    def __init__(self, returncode, error_message):
        '''
        '''

        self.returncode = status_code
        self.error_message = error_message
        super().__init__("ERROR {}: {}".format(self.returncode, self.error_message))


class ReceiptNotFoundError(SignalException):
    pass
