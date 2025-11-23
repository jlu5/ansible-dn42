#!/usr/bin/env python3
import pycountry

class FilterModule():

    def _flag(self, alpha_2_code: str):
        if alpha_2_code == 'UK':
            alpha_2_code = 'GB'
        return pycountry.countries.get(alpha_2=alpha_2_code).flag

    def filters(self):
        return {
            'flag': self._flag
        }
