"""Tests for utility functions."""

from lazy_ecs.core.utils import batch_items


def test_batch_items_basic():
    items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    batches = list(batch_items(items, 3))

    assert len(batches) == 4
    assert batches[0] == [1, 2, 3]
    assert batches[1] == [4, 5, 6]
    assert batches[2] == [7, 8, 9]
    assert batches[3] == [10]


def test_batch_items_exact_fit():
    items = [1, 2, 3, 4, 5, 6]
    batches = list(batch_items(items, 3))

    assert len(batches) == 2
    assert batches[0] == [1, 2, 3]
    assert batches[1] == [4, 5, 6]


def test_batch_items_single_batch():
    items = [1, 2, 3]
    batches = list(batch_items(items, 10))

    assert len(batches) == 1
    assert batches[0] == [1, 2, 3]


def test_batch_items_empty_list():
    items = []
    batches = list(batch_items(items, 5))

    assert len(batches) == 0


def test_batch_items_size_one():
    items = [1, 2, 3, 4, 5]
    batches = list(batch_items(items, 1))

    assert len(batches) == 5
    assert batches[0] == [1]
    assert batches[1] == [2]
    assert batches[2] == [3]
    assert batches[3] == [4]
    assert batches[4] == [5]


def test_batch_items_strings():
    items = ["a", "b", "c", "d", "e", "f", "g"]
    batches = list(batch_items(items, 3))

    assert len(batches) == 3
    assert batches[0] == ["a", "b", "c"]
    assert batches[1] == ["d", "e", "f"]
    assert batches[2] == ["g"]
