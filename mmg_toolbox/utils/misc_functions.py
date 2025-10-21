"""
Miscellaneous functions
"""

import re
import numpy as np
from typing import Any
from collections import defaultdict


regex_number = re.compile(r'\d{3,}')
re_long_floats = re.compile(r'\d+\.\d{5,}')


def consolidate_strings(*args: tuple, match_symbol: str = '*', match_score: float = 0.6) -> list:
    """
    Consolidate list of strings by finding matching components and
    replace differences with a symbol
    :param args: list of strings
    :param match_symbol: str to replace non-matching
    :param match_score: float 0-1, difference score greater than this will be replaced
    :returns: reduced list of strings
    """
    new_list = set()  # create a set to remove duplicates
    matched_index = []
    for idx_a, a in enumerate(args[:-1]):
        if idx_a in matched_index:
            continue
        for idx_b, b in enumerate(args[idx_a+1:]):
            if len(a) == len(b):
                if sum(1 for n in range(len(a)) if a[n] == b[n]) / len(a) > match_score:
                    a = ''.join(a[n] if a[n] == b[n] else match_symbol for n in range(len(a)))
                    matched_index.append(idx_b + idx_a + 1)
        new_list.add(a)
    return list(new_list)


def consolidate_numeric_strings(*args: str) -> list:
    """
    Consolidate list of strings by finding numbers in strings
    :param args: list of strings
    :returns: reduced list of strings
    """
    strings = defaultdict(list)
    reset_strings = {}
    for arg in args:
        match = regex_number.search(arg)
        if match:
            number = int(match[0])
            new_str = regex_number.sub('####', arg)
            strings[new_str] += [number]
            reset_strings[new_str] = arg

    out = [
        f"{string} .. [{numbers2string(numbers)}]"
        if len(numbers) > 1 else reset_strings[string]
        for string, numbers in strings.items()
    ]
    return out


def findranges(scannos: list[int], sep=':') -> str:
    """
    Convert a list of numbers to a simple string
    E.G.
    findranges([1,2,3,4,5]) = '1:5'
    findranges([1,2,3,4,5,10,12,14,16]) = '1:5,10:2:16'
    """

    scannos = np.sort(scannos).astype(int)

    dif = np.diff(scannos)

    stt, stp, rng = [scannos[0]], [dif[0]], [1]
    for n in range(1, len(dif)):
        if scannos[n + 1] != scannos[n] + dif[n - 1]:
            stt += [scannos[n]]
            stp += [dif[n]]
            rng += [1]
        else:
            rng[-1] += 1
    stt += [scannos[-1]]
    rng += [1]

    out = []
    x = 0
    while x < len(stt):
        if rng[x] == 1:
            out += ['{}'.format(stt[x])]
            x += 1
        elif stp[x] == 1:
            out += ['{}{}{}'.format(stt[x], sep, stt[x + 1])]
            x += 2
        else:
            out += ['{}{}{}{}{}'.format(stt[x], sep, stp[x], sep, stt[x + 1])]
            x += 2
    return ','.join(out)


def numbers2string(scannos: list[int], sep=':') -> str:
    """
    Convert a list of numbers to a simple string
    E.G.
    numbers2string([50001,50002,50003]) = '5000[1:3]'
    numbers2string([51020,51030,51040]) = '510[20:10:40]'
    """

    if type(scannos) is str or type(scannos) is int or len(scannos) == 1:
        return str(scannos)

    scannos = np.sort(scannos).astype(str)

    n = len(scannos[0])
    while np.all([scannos[0][:-n] == x[:-n] for x in scannos]):
        n -= 1

    if n == len(scannos[0]):
        return '{}-{}'.format(scannos[0], scannos[-1])

    inistr = scannos[0][:-(n + 1)]
    strc = [i[-(n + 1):] for i in scannos]
    liststr = findranges(strc, sep=sep)
    return '{}[{}]'.format(inistr, liststr)


def round_string_floats(string: str) -> str:
    """
    Shorten string by removing long floats
    :param string: string, e.g. '#810002 scan eta 74.89533603616637 76.49533603616636 0.02 pil3_100k 1 roi2'
    :return: shorter string, e.g. '#810002 scan eta 74.895 76.495 0.02 pil3_100k 1 roi2'
    """
    def subfun(m):
        return str(round(float(m.group()), 3))
    return re_long_floats.sub(subfun, string)


def stfm(value: float, error: float) -> str:
    """
    Create standard form string from value and uncertainty"
     str = stfm(val,err)
     Examples:
          '35.25 (1)' = stfm(35.25,0.01)
          '110 (5)' = stfm(110.25,5)
          '0.0015300 (5)' = stfm(0.00153,0.0000005)
          '1.56(2)E+6' = stfm(1.5632e6,1.53e4)

    Notes:
     - Errors less than 0.01% of values will be given as 0
     - The maximum length of string is 13 characters
     - Errors greater than 10x the value will cause the value to be rounded to zero
    """

    # Determine the number of significant figures from the error
    if error == 0. or value / float(error) >= 1E5:
        # Zero error - give value to 4 sig. fig.
        out = '{:1.5G}'.format(value)
        if 'E' in out:
            out = '{}(0)E{}'.format(*out.split('E'))
        else:
            out = out + ' (0)'
        return out
    elif np.log10(np.abs(error)) > 0.:
        # Error > 0
        sigfig = np.ceil(np.log10(np.abs(error))) - 1
        dec = 0.
    elif np.isnan(error):
        # nan error
        return '{} (-)'.format(value)
    else:
        # error < 0
        sigfig = np.floor(np.log10(np.abs(error)) + 0.025)
        dec = -sigfig

    # Round value and error to the number of significant figures
    rval = round(value / (10. ** sigfig)) * (10. ** sigfig)
    rerr = round(error / (10. ** sigfig)) * (10. ** sigfig)
    # size of value and error
    pw = np.floor(np.log10(np.abs(rval)))
    pwr = np.floor(np.log10(np.abs(rerr)))

    max_pw = max(pw, pwr)
    ln = max_pw - sigfig  # power difference

    if np.log10(np.abs(error)) < 0:
        rerr = error / (10. ** sigfig)

    # Small numbers - exponential notation
    if max_pw < -3.:
        rval = rval / (10. ** max_pw)
        fmt = '{' + '0:1.{:1.0f}f'.format(ln) + '}({1:1.0f})E{2:1.0f}'
        return fmt.format(rval, rerr, max_pw)

    # Large numbers - exponential notation
    if max_pw >= 4.:
        rval = rval / (10. ** max_pw)
        rerr = rerr / (10. ** sigfig)
        fmt = '{' + '0:1.{:1.0f}f'.format(ln) + '}({1:1.0f})E+{2:1.0f}'
        return fmt.format(rval, rerr, max_pw)

    fmt = '{' + '0:0.{:1.0f}f'.format(dec + 0) + '} ({1:1.0f})'
    return fmt.format(rval, rerr)


def shorten_string(string: str, max_length: int = 100) -> str:
    """Return a shortend version of the first line of the string"""
    string = string.splitlines().strip()
    string = round_string_floats(string)
    if len(string) < max_length:
        return string 
    return string[:max_length-3] + '...'


class DataHolder(dict):
    """
    Convert dict to object that looks like a class object with key names as attributes
    Replicates slightly the old scisoftpy.dictutils.DataHolder class, also known as DLS dat format.
        obj = DataHolder(**{'item1': 'value1'})
        obj['item1'] -> 'value1'
        obj.item1 -> 'value1'
        obj.keys() -> dict.keys()
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for name in kwargs:
            setattr(self, name, kwargs[name])
            self.update({name: kwargs[name]})


def data_holder(scan_data: dict[str, np.ndarray], metadata: dict[str, Any]) -> DataHolder:
    """
    Create DataHolder object from scan data and metadata
    Return object that slightly replicates the old scisoftpy.dictutils.DataHolder class, also known as DLS dat format.
    """
    d = DataHolder(**scan_data)
    d.metadata = DataHolder(**metadata)
    return d

