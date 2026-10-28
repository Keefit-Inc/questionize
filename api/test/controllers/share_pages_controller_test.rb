require "test_helper"

class SharePagesControllerTest < ActionDispatch::IntegrationTest
  test "a public question gets social preview tags without its answer" do
    item = create_item(correct_label: "D")
    item.current_version.update!(stem: %(Which "best" <weakens> the argument?))
    get share_page_path(item.public_id)

    assert_response :ok
    assert_select "meta[property='og:title'][content*='Can you solve this?']"
    assert_select "meta[name='twitter:card'][content='summary_large_image']"
    assert_select "title", count: 1
    assert_select "meta[property='og:url'][content$='/q/#{item.public_id}']"
    assert_includes response.body, "Which &quot;best&quot; &lt;weakens&gt; the argument?"
    assert_not_includes response.body, item.current_version.explanation
  end

  test "private and unknown items get the plain app shell" do
    item = create_item(visibility: "private")
    get share_page_path(item.public_id)
    assert_response :ok
    assert_select "meta[property='og:title']", false
    get share_page_path("nope")
    assert_select "meta[property='og:title']", false
  end

  test "client-side routes serve the app, API routes do not" do
    get "/me"
    assert_response :ok
    assert_select "#app"
  end
end
