import gc

from miro import app
from miro import messages
from miro import models
from miro import search
from miro import ngrams
from miro import itemsource
from miro.item import FeedParserValues
from miro.singleclick import _build_entry
from miro.test.framework import MiroTestCase
from miro.frontends.widgets.search import SearchFilter

class NGramTest(MiroTestCase):
    def test_simple(self):
        results = ngrams.breakup_word('foobar', 2, 3)
        self.assertSameSet(results, [
            'fo', 'oo', 'ob', 'ba', 'ar',
            'foo', 'oob', 'oba', 'bar'])

    def test_list(self):
        word_list = ['foo', 'bar', 'bazbaz']
        results = ngrams.breakup_list(word_list, 2, 3)
        self.assertSameSet(results, [
                'fo', 'oo', 'foo',
                'ba', 'ar', 'bar',
                'az', 'zb', 'baz', 'azb', 'zba'])

    def test_memory(self):
        # make sure we aren't leaking memory in our C module
        gc.collect()
        start_count = len(gc.get_objects())
        results = ngrams.breakup_list(['foo', 'bar', 'bazbaz'], 1, 3)
        results2 = ngrams.breakup_word('miroiscool', 1, 3)
        del results
        del results2
        gc.collect()
        end_count = len(gc.get_objects())
        self.assertEquals(start_count, end_count)

class SearchTest(MiroTestCase):
    def setUp(self):
        MiroTestCase.setUp(self)
        self.feed = models.Feed(u'http://example.com/')
        self.item1 = self.make_item(u'http://example.com/', u'my first item')
        self.item2 = self.make_item(u'http://example.com/', u'my second item')

    def make_item(self, url, title=u'default item title'):
        additional = {'title': title}
        entry = _build_entry(url, 'video/x-unknown', additional)
        item = models.Item(FeedParserValues(entry), feed_id=self.feed.id)
        return itemsource.DatabaseItemSource._item_info_for(item)

    def assertMatches(self, query, item_info):
        self.assertTrue(search.item_matches(item_info, query))

    def assertNotMatches(self, query, item_info):
        self.assertFalse(search.item_matches(item_info, query))

    def test_item_matches(self):
        self.assertMatches('first', self.item1)
        self.assertNotMatches('first', self.item2)
        self.assertMatches('second', self.item2)
        self.assertNotMatches('second', self.item1)
        self.assertMatches('my', self.item1)
        self.assertMatches('my', self.item2)
        self.assertNotMatches('foo', self.item1)
        self.assertNotMatches('foo', self.item2)

    def test_item_matches_substring(self):
        self.assertMatches('eco', self.item2)
        self.assertNotMatches('eco', self.item1)
        self.assertMatches('irst', self.item1)
        self.assertNotMatches('irst', self.item2)

    def test_item_matches_short(self):
        self.assertMatches('d', self.item2)
        self.assertNotMatches('d', self.item1)
        self.assertMatches('', self.item1)
        self.assertMatches('', self.item2)

    def test_item_matches_case_insensitive(self):
        self.assertMatches('FiRsT', self.item1)
        self.assertNotMatches('FiRsT', self.item2)
        self.assertMatches('sEcOnD', self.item2)
        self.assertNotMatches('sEcOnD', self.item1)

    def test_list_matches(self):
        items = [self.item1, self.item2]
        self.assertEquals(list(search.list_matches(items, 'first')),
                          [self.item1])
        self.assertEquals(list(search.list_matches(items, 'second')),
                          [self.item2])
        self.assertEquals(list(search.list_matches(items, 'my')),
                          [self.item1, self.item2])
        self.assertEquals(list(search.list_matches(items, 'foo')),
                          [])

    def test_ngrams_for_term(self):
        self.assertEquals(search._ngrams_for_term('a'),
                ['a'])
        self.assertEquals(search._ngrams_for_term('five'),
                ['five'])
        self.assertEquals(search._ngrams_for_term('verybig'),
                ['veryb', 'erybi', 'rybig'])

class ItemSearcherTest(MiroTestCase):
    def setUp(self):
        MiroTestCase.setUp(self)
        self.searcher = search.ItemSearcher()
        self.feed = models.Feed(u'http://example.com/')
        self.item1 = self.make_item(u'http://example.com/', u'my first item')
        self.item2 = self.make_item(u'http://example.com/', u'my second item')

    def make_item(self, url, title=u'default item title'):
        additional = {'title': title}
        entry = _build_entry(url, 'video/x-unknown', additional)
        item = models.Item(FeedParserValues(entry), feed_id=self.feed.id)
        self.searcher.add_item(self.make_info(item))
        return item

    def make_info(self, item):
        return itemsource.DatabaseItemSource._item_info_for(item)

    def check_search_results(self, search_text, *correct_items):
        correct_ids = [i.id for i in correct_items]
        self.assertSameSet(self.searcher.search(search_text), correct_ids)

    def check_empty_result(self, search_text):
        self.assertSameSet(self.searcher.search(search_text), [])

    def test_match(self):
        self.check_search_results('my', self.item1, self.item2)
        self.check_search_results('first', self.item1)
        self.check_empty_result('miro')

    def test_update(self):
        self.item1.set_title(u'my new title')
        self.searcher.update_item(self.make_info(self.item1))
        self.check_search_results('my', self.item1, self.item2)
        self.check_search_results('item', self.item2)
        self.check_search_results('title', self.item1)
        self.check_empty_result('first')

    def test_remove(self):
        self.searcher.remove_item(self.make_info(self.item2).id)
        self.check_search_results('my', self.item1)
        self.check_empty_result('second')

class SearchFilterTest(MiroTestCase):
    def setUp(self):
        MiroTestCase.setUp(self)
        self.feed = models.Feed(u'http://example.com/')
        self.initial_list = []
        self.added_objects = []
        self.changed_objects = []
        self.removed_objects = []
        self.filterer = self.make_filterer()
        self.info1 = self.make_info(u'info one')
        self.info2 = self.make_info(u'info two')
        self.info3 = self.make_info(u'info three')
        self.info4 = self.make_info(u'info four')

    def make_filterer(self):
        filterer = SearchFilter()
        filterer.connect("initial-list", self.on_initial_list)
        filterer.connect("items-changed", self.on_items_changed)
        return filterer

    def make_info(self, title):
        additional = {'title': title}
        url = u'http://example.com/'
        entry = _build_entry(url, 'video/x-unknown', additional)
        item = models.Item(FeedParserValues(entry), feed_id=self.feed.id)
        return itemsource.DatabaseItemSource._item_info_for(item)

    def on_initial_list(self, filterer, objects):
        if self.initial_list:
            raise AssertionError("Got initial list twice")
        self.initial_list = objects

    def on_items_changed(self, filterer, added, changed, removed):
        self.added_objects.extend(added)
        self.changed_objects.extend(changed)
        self.removed_objects.extend(removed)

    def check_initial_list_callback(self, infos):
        self.assertSameSet(self.initial_list, infos)

    def check_changed_callbacks(self, added, changed, removed):
        removed = [i.id for i in removed]
        self.assertSameSet(self.added_objects, added)
        self.assertSameSet(self.changed_objects, changed)
        self.assertSameSet(self.removed_objects, removed)

    def clear_callback_objects(self, clear_initial_list=False):
        self.added_objects = []
        self.changed_objects = []
        self.removed_objects = []
        if clear_initial_list:
            self.initial_list = []

    def send_item_list_message(self, infos):
        message = messages.ItemList('mytpe', 123, infos)
        self.filterer.handle_item_list(message)

    def send_items_changed_message(self, added, changed, removed):
        removed = [i.id for i in removed]
        message = messages.ItemsChanged('mytpe', 123, added, changed, removed)
        self.filterer.handle_items_changed(message)

    def update_info(self, info, name):
        info.name = name
        info.search_ngrams = search.calc_ngrams(info)

    def test_initial_list(self):
        # try with no search just to see
        self.send_item_list_message([self.info1, self.info2])
        self.check_initial_list_callback([self.info1, self.info2])
        self.check_changed_callbacks([], [], [])
        # try again with a search set
        self.clear_callback_objects(clear_initial_list=True)
        self.filterer = self.make_filterer()
        self.filterer.set_search("two")
        self.send_item_list_message([self.info1, self.info2])
        self.check_initial_list_callback([self.info2])
        self.check_changed_callbacks([], [], [])

    def test_change_search(self):
        # setup initial state
        self.send_item_list_message([self.info1, self.info2])
        self.clear_callback_objects()
        # try changing the search
        self.filterer.set_search("two")
        # info1 doesn't match the search, it should be removed
        self.check_changed_callbacks([], [], [self.info1])

        self.clear_callback_objects()
        self.filterer.set_search("one")
        # info1 matches now, item2 doesn't
        self.check_changed_callbacks([self.info1], [], [self.info2])

    def test_add(self):
        # setup initial state
        self.send_item_list_message([self.info1, self.info2])
        self.filterer.set_search("three")
        self.clear_callback_objects()
        # see what happens when new objects come in
        self.send_items_changed_message([self.info3, self.info4], [], [])
        # only info3 matched the search, it should be the only one added
        self.check_changed_callbacks([self.info3], [], [])

    def test_update(self):
        # setup initial state
        self.send_item_list_message([self.info1, self.info2, self.info3])
        self.filterer.set_search("three")
        self.clear_callback_objects()
        # see what happens when objects change
        self.update_info(self.info1, u'three')
        self.send_items_changed_message([],
                [self.info1, self.info2, self.info3], [])
        # info1 now matches the search, it should be added
        # info3 matched the search before and now, so it should be changed
        self.check_changed_callbacks([self.info1], [self.info3], [])
        # try it a different way
        self.clear_callback_objects()
        self.update_info(self.info1, u'one')
        self.send_items_changed_message([],
                [self.info1, self.info2, self.info3], [])
        # info1 no longer matches the search, it should be added
        # info3 matched the search before and now, so it should be changed
        self.check_changed_callbacks([], [self.info3], [self.info1])

    def test_remove(self):
        # setup initial state
        self.send_item_list_message([self.info1, self.info2])
        self.filterer.set_search("two")
        self.clear_callback_objects()
        # see what happens when objects are removed
        self.send_items_changed_message([], [], [self.info1, self.info2])
        # only info2 matched the search, so removed should only include it
        self.check_changed_callbacks([], [], [self.info2])
