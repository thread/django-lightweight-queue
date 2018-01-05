class RedisCleanupMixin(object):
    client = None
    prefix = None

    def setUp(self):
        super(RedisCleanupMixin, self).setUp()
        self.assertIsNotNone(self.client, "Need a redis client to be provided")

    def tearDown(self):
        root = '*'
        if self.prefix is not None:
            root = '%s*' % (self.prefix,)

        keys = self.client.keys(root)
        for key in keys:
            self.client.delete(key)

        super(RedisCleanupMixin, self).tearDown()
