# Genius Invokation TCG, write in python.
# Copyright (C) 2023 Asassong
#
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

class Entity:
    def __init__(self):
        self.name = ""
        self._usage = 1
        self.count = 0
        self.counter_name = ""
        self.record = []
        self.need_remove = False
        self.modifies = []

    def get_name(self):
        return self.name

    def add_record(self, value):
        self.record.append(value)

    def clear_record(self):
        self.record.clear()

    def get_count(self):
        return self.count

    def add_counter(self, counter_name):
        self.counter_name = counter_name

    def get_usage(self):
        return self._usage

    def consume_usage(self, value):
        self._usage -= value
        if self._usage <= 0:
            self.need_remove = True

    def set_usage(self, value):
        self._usage = value
        if self._usage <= 0:
            self.need_remove = True

