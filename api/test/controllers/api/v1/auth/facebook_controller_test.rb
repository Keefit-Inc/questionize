require "test_helper"

class Api::V1::Auth::FacebookControllerTest < ActionDispatch::IntegrationTest
  APP = { app_id: "123", app_secret: "s3cret" }.freeze

  setup do
    @config = Rails.application.config.x.facebook
    @saved = { app_id: @config.app_id, app_secret: @config.app_secret }
    @config.app_id = APP[:app_id]
    @config.app_secret = APP[:app_secret]
    @user = User.create!
  end

  teardown do
    @config.app_id = @saved[:app_id]
    @config.app_secret = @saved[:app_secret]
  end

  # Stands in for the Graph API: a valid token for user 42 issued to our app.
  def with_graph(valid: true, app_id: APP[:app_id], uid: "42", &block)
    graph = lambda do |path, params|
      if path == "/debug_token"
        { "data" => { "is_valid" => valid, "app_id" => app_id, "user_id" => uid } }
      else
        assert_equal OpenSSL::HMAC.hexdigest("SHA256", APP[:app_secret], params[:access_token]), params[:appsecret_proof]
        { "id" => uid, "name" => "Ada Reader", "email" => "ada@example.com" }
      end
    end
    Auth::Facebook.graph_client = graph
    block.call
  ensure
    Auth::Facebook.graph_client = nil
  end

  def login(user = @user)
    post api_v1_auth_facebook_path, params: { access_token: "tok" }, headers: auth_headers(user), as: :json
  end

  test "config exposes the public app id only" do
    get api_v1_config_path
    assert_equal({ "facebook_app_id" => "123" }, response.parsed_body)
  end

  test "a first login links Facebook to this device's user" do
    with_graph { login }
    assert_response :success
    assert_equal [ @user.api_token, false ], [ response.parsed_body["token"], response.parsed_body["switched"] ]
    assert_equal [ "facebook", "42", "Ada Reader" ], @user.identities.sole.slice(:provider, :uid, :name).values
    assert_not @user.reload.anonymous
  end

  test "logging in on a new device switches to the existing account and brings its snapped questions" do
    with_graph { login }
    phone = User.create!
    run = GenerationRun.create!(user: phone, kind: "error_log", params: {})
    GenerationRuns::Recorder.new(run).record(diagnosis_event)
    with_graph { login(phone) }
    assert_equal [ @user.api_token, true ], [ response.parsed_body["token"], response.parsed_body["switched"] ]
    assert_equal 1, @user.error_log_entries.count
    assert_equal 0, phone.error_log_entries.count
  end

  test "tokens for another app or that are invalid are refused" do
    with_graph(app_id: "999") { login }
    assert_response :unauthorized
    with_graph(valid: false) { login }
    assert_response :unauthorized
    assert_empty UserIdentity.all
  end

  test "Facebook's data deletion callback deletes the account" do
    with_graph { login }
    payload = Base64.urlsafe_encode64({ algorithm: "HMAC-SHA256", user_id: "42" }.to_json, padding: false)
    sig = Base64.urlsafe_encode64(OpenSSL::HMAC.digest("SHA256", APP[:app_secret], payload), padding: false)
    post api_v1_auth_facebook_data_deletion_path, params: { signed_request: "#{sig}.#{payload}" }
    assert_response :success
    assert response.parsed_body["confirmation_code"].present?
    assert_not User.exists?(@user.id)

    post api_v1_auth_facebook_data_deletion_path, params: { signed_request: "bad.#{payload}" }
    assert_response :bad_request
  end

  test "a learner can delete their own account" do
    run = GenerationRun.create!(user: @user, kind: "error_log", params: { "book" => "Workbook" })
    GenerationRuns::Recorder.new(run).record(diagnosis_event)
    post api_v1_item_feedback_path(run.items.first.public_id), params: { kind: "up" }, headers: auth_headers(@user), as: :json
    delete api_v1_me_path, headers: auth_headers(@user)
    assert_response :no_content
    assert_not User.exists?(@user.id)
    assert_equal 0, Learning::ErrorLogEntry.count
    assert_equal 2, Item.count, "shared practice questions stay in the bank"
  end
end
