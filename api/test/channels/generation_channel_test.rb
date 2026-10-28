require "test_helper"

class GenerationChannelTest < ActionCable::Channel::TestCase
  setup do
    @owner = User.create!
    @run = GenerationRun.create!(user: @owner)
  end

  test "the run's owner can subscribe" do
    stub_connection current_user: @owner
    subscribe run_id: @run.id
    assert subscription.confirmed?
    assert_has_stream_for @run
  end

  test "other users are rejected" do
    stub_connection current_user: User.create!
    subscribe run_id: @run.id
    assert subscription.rejected?
  end
end

class ApplicationCable::ConnectionTest < ActionCable::Connection::TestCase
  test "connects with a valid token and rejects without one" do
    user = User.create!
    connect params: { token: user.api_token }
    assert_equal user, connection.current_user
    assert_reject_connection { connect params: { token: "nope" } }
  end
end
