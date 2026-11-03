class PlaythingRetSelf:
    __slots__ = ()

    def _mock(self, *args, **kwargs):
        return args[0]

    __iter__ = __setattr__ = __getattr__ = __getitem__ = __setitem__ = __call__ = _mock


a = PlaythingRetSelf()
print(a.nya)
