require "test_helper"

class SpaControllerTest < ActionDispatch::IntegrationTest
  test "the app shell is served for / and client routes and is never cached" do
    [ "/", "/snap", "/questions", "/misses/12" ].each do |path|
      get path, headers: { "Accept" => "text/html" }
      assert_response :success
      assert_includes response.body, %(<div id="app">)
      assert_equal "no-cache", response.headers["Cache-Control"]
    end
  end
end
