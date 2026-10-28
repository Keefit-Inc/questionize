require "test_helper"

class ItemChannelTest < ActionCable::Channel::TestCase
  setup do
    @user = User.create!
    @item = create_item
  end

  test "only learners who answered can watch the live tally" do
    stub_connection current_user: @user
    subscribe item_id: @item.public_id
    assert subscription.rejected?

    Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "A")
    subscribe item_id: @item.public_id
    assert subscription.confirmed?
    assert_has_stream_for @item
  end
end
