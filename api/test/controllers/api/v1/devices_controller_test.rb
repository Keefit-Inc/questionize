require "test_helper"

class Api::V1::DevicesControllerTest < ActionDispatch::IntegrationTest
  test "creates an anonymous user and returns its token" do
    assert_difference -> { User.count }, 1 do
      post api_v1_devices_path, as: :json
    end
    assert_response :created
    body = response.parsed_body
    user = User.find_by!(api_token: body["token"])
    assert user.anonymous
    assert_equal user.handle, body.dig("user", "handle")
  end
end
