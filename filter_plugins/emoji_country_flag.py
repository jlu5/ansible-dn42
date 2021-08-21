#!/usr/bin/env python3
import flag  # https://pypi.org/project/emoji-country-flag/

class FilterModule():
    def filters(self):
        return {
            'flagize': flag.flagize,
            'dflagize': flag.dflagize,
            'flag': flag.flag
        }
