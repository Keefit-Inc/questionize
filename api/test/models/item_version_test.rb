require "test_helper"

class ItemVersionTest < ActiveSupport::TestCase
  test "requires one choice and one rationale per label" do
    item = create_item
    version = item.current_version.dup
    version.version = 2
    version.choices = version.choices.first(4)
    assert_not version.valid?
    assert_includes version.errors[:choices].first, "A-E"
  end

  test "items get a public id and roll skills up to family and overall" do
    item = create_item(family: "RC", subtype: "inference")
    assert_match(/\A[[:alnum:]]{10}\z/, item.public_id)
    assert_equal %w[RC:inference RC overall], item.skill_chain
  end
end
