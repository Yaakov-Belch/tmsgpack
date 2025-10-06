from tmsgpack import basic_codec, __version__

print(f'{__version__=}')

def main():
    check_round_trip(range(-2000, 2000), 'small integers')
    check_round_trip([
       s * (2**e + d)
       for e in range(63)
       for d in range(-10, 10)
       for s in (-1, +1)
    ], 'integers')
    check_round_trip([3.1415926], 'float')
    check_round_trip([
       v
       for e in range(18)
       for d in range(-2, 2)
       for f in (1, 1/3)
       for n in [int(f * 2**e + d)]
       for v in [
           "*"*n,
           b"*"*n,
           [12]*n,
           (12,)*n,
           {m:3*m+1 for m in range(n)},
       ]
    ], 'strings, bytes, lists, tuples, dicts')
    check_round_trip([True, False, None], 'constants: True False None')
    check_round_trip([[
        1,2,3,4, {'a':'hello', 'b': ['world', 5,6,7]},
    ]], 'nested value')

def check_round_trip(values, comment=''):
    ok = not_ok = 0
    for value in values:
        msg = basic_codec.encode(value)
        new_value = basic_codec.decode(msg)
        if new_value == value: ok += 1
        else:
            not_ok += 1
            print('----- Different -------')
            print(value)
            print(new_value)
            print('-----------------------')

    print(f'{ok=} {not_ok=} {comment}')

if __name__ == '__main__':
    main()
