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

  test "page addresses work for crawlers that don't ask for HTML; missing files stay 404" do
    get "/privacy", headers: { "Accept" => "*/*", "User-Agent" => "facebookexternalhit/1.1" }
    assert_response :success
    assert_includes response.body, %(<div id="app">)
    get "/privacy"
    assert_response :success
    get "/web-assets/missing.js"
    assert_response :not_found
    get "/api/v1/nothing-here", headers: { "Accept" => "*/*" }
    assert_response :not_found
  end
end
