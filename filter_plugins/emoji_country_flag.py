#!/usr/bin/env python3
import flag  # https://pypi.org/project/emoji-country-flag/

class FilterModule():

    def _flag(self, text):
        if text == 'UK':
            text = 'GB'
        return flag.flag(text)

    def filters(self):
        return {
            'flagize': flag.flagize,
            'dflagize': flag.dflagize,
            'flag': self._flag
        }
