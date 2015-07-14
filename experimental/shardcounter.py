import random

from google.appengine.api import memcache
from google.appengine.ext import ndb


SHARD_KEY_TEMPLATE = 'shard-{}-{:d}'


class GeneralCounterShardConfig(ndb.Model):
    num_shards = ndb.IntegerProperty(default=20)
    
    @classmethod
    def all_keys(cls, name):
        config = cls.get_or_insert(name)
        shard_key_strings = [SHARD_KEY_TEMPLATE.format(name, index) for index in range(config.num_shards)]
        return [ndb.Key(GeneralCounterShard, shard_key_string) for shard_key_string in shard_key_strings]


class GeneralCounterShard(ndb.Model):
    count = ndb.IntegerProperty(default=0)

def get_count(name):
    total = memcache.get(name)
    if total is None:
        total = 0
        all_keys = GeneralCounterShardConfig.all_keys(name)
        for counter in ndb.get_multi(all_keys):
            if counter is not None:
                total += counter.count
        memcache.add(name, total, 7200) # 2 hours to expire
    return total


def increment(name):
    config = GeneralCounterShardConfig.get_or_insert(name)
    return _increment(name, config.num_shards)


@ndb.transactional
def _increment(name, num_shards):
    index = random.randint(0, num_shards - 1)
    shard_key_string = SHARD_KEY_TEMPLATE.format(name, index)
    counter = GeneralCounterShard.get_by_id(shard_key_string)

    if counter is None:
        counter = GeneralCounterShard(id=shard_key_string)

    counter.count += 1
    counter.put()
    
    rval = memcache.incr(name) # Memcache increment does nothing if the name is not a key in memcache

    if rval is None:
        return get_count(name)
    return rval


@ndb.transactional
def increase_shards(name, num_shards):
    config = GeneralCounterShardConfig.get_or_insert(name)
    if config.num_shards < num_shards:
        config.num_shards = num_shards
        config.put()