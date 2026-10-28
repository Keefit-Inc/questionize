require "test_helper"

class SourceTest < ActiveSupport::TestCase
  test "tracking links and cosmetic differences map to one canonical url" do
    a = Source.canonicalize("http://www.Example.com/news/story/?utm_source=x&b=2&a=1#comments")
    b = Source.canonicalize("https://example.com/news/story?a=1&b=2&fbclid=abc")
    assert_equal "https://example.com/news/story?a=1&b=2", a
    assert_equal a, b
  end

  test "rejects non-web urls" do
    assert_raises(URI::InvalidURIError) { Source.canonicalize("chrome://extensions") }
    assert_raises(URI::InvalidURIError) { Source.canonicalize("") }
  end

  test "for_page! reuses the source and stores only a hash of the text" do
    first = Source.for_page!(url: "https://example.com/a?utm_medium=x", title: "A", text: ARTICLE_TEXT)
    second = Source.for_page!(url: "https://www.example.com/a", title: "", text: ARTICLE_TEXT)
    assert_equal first, second
    assert_equal "A", second.title
    assert_equal "example.com", second.domain
    assert_equal 64, second.content_hash.length
  end
end
