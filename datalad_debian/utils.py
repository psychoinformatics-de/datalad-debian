

def result_matches(res, **kwargs) -> bool:
    """Test whether a (result) dict matches given key/value combinations.

    Parameters
    ----------
    res: dict
      Result dictionary to inspect.
    **kwargs:
      key-value pairs to match. For each key, the value in `res` has to
      match the value to given value. Multiple candidate values can be
      given as a tuple or a list value for a given key. If the target
      value in `res` is a tuple or list, the `kwargs` value must be
      wrapped into a tuple.

    Returns
    -------
    bool
      True if `res` matches all key/value specifications in `kwargs`,
      and False otherwise.
    """
    if not hasattr(res, 'items'):
        raise ValueError('Argument must be dict-like')

    # special internal type that could not possibly come from outside
    # which we can use to streamline our tests here
    class NotHere():
        pass

    for k, v in kwargs.items():
        if not isinstance(v, (list, tuple)):
            # normalize for "is in" test
            v = (v,)
        if res.get(k, NotHere) not in v:
            # either `k` was not in `res, or the value does not match
            return False
    return True



