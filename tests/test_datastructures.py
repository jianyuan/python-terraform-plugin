from terraform import datastructures, settings


def test_resource_data_set_id():
    test_id = "test-id"
    data = datastructures.ResourceData()

    data.set_id(test_id)

    assert data[settings.ID_KEY] == test_id
