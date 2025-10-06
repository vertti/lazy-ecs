"""Tests for utility functions."""

from lazy_ecs.core.utils import batch_items


def test_batch_items_basic():
    batches = list(batch_items([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 3))

    assert batches == [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]


def test_batch_items_exact_fit():
    batches = list(batch_items([1, 2, 3, 4, 5, 6], 3))

    assert batches == [[1, 2, 3], [4, 5, 6]]


def test_batch_items_single_batch():
    batches = list(batch_items([1, 2, 3], 10))

    assert batches == [[1, 2, 3]]


def test_batch_items_empty_list():
    batches = list(batch_items([], 5))

    assert batches == []


def test_batch_items_size_one():
    batches = list(batch_items([1, 2, 3, 4, 5], 1))

    assert batches == [[1], [2], [3], [4], [5]]


def test_batch_items_strings():
    batches = list(batch_items(["a", "b", "c", "d", "e", "f", "g"], 3))

    assert batches == [["a", "b", "c"], ["d", "e", "f"], ["g"]]
