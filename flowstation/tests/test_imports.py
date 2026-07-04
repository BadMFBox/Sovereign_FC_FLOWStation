"""Small test to ensure the stubs import correctly."""


def test_imports():
    import flowstation.burners as b
    import flowstation.assets as a
    import flowstation.core as c
    assert hasattr(b, 'generate_token')
    assert hasattr(a, 'get_asset_path')
    assert hasattr(c, 'FlowState')
