import pytest
from verlib.auth import AccessLevel


@pytest.fixture
def acl() -> AccessLevel:
    return AccessLevel()


def test_aclevel_or_works(acl: AccessLevel):
    other = AccessLevel()
    combined_acl = acl | other
    assert id(acl) in combined_acl._acls_ids
    assert id(other) in combined_acl._acls_ids


def test_clears_method_works(acl: AccessLevel):
    test_acl = AccessLevel()
    test_acl_1 = AccessLevel()

    test_acl_combo = acl | test_acl_1

    assert not acl._acls_ids.issuperset(test_acl_combo._acls_ids)

    assert not acl.clears(test_acl_combo)
    assert not test_acl_1.clears(test_acl_combo)
    assert test_acl_combo.clears(acl)
    assert test_acl_combo.clears(test_acl_1)

    test_acl_combo = acl | test_acl
    assert not acl.clears(test_acl_combo)
    assert not test_acl.clears(test_acl_combo)
    assert test_acl_combo.clears(acl)
    assert test_acl_combo.clears(test_acl)


def test_public_private_acl_work():
    assert AccessLevel.public.clears(AccessLevel.public)
    assert AccessLevel.private.clears(AccessLevel.private)
    assert not AccessLevel.public.clears(AccessLevel.private)
    assert AccessLevel.private.clears(AccessLevel.private)
    pass
