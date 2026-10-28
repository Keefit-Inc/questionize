# GET /q/:public_id — the web app with Open Graph / Twitter tags for a public question, so a
# shared link previews as a card. Only public items get a preview; nothing reveals the answer.
class SharePagesController < SpaController
  def show
    item = Item.listed.includes(:current_version).find_by(public_id: params[:public_id])
    html = index_html
    html = html.sub(%r{<title>.*?</title>}m, "").sub("</head>", "#{meta_tags(item)}</head>") if item
    render html: html.html_safe, layout: false # tag values are escaped in meta_tags
  end

  private

  def meta_tags(item)
    family = { "CR" => "Critical Reasoning", "RC" => "Reading Comprehension", "SC" => "Sentence Correction" }.fetch(item.family)
    title = "Can you solve this? · #{family} · Questionize"
    tried = item.attempts_count.positive? ? " #{helpers.pluralize(item.attempts_count, 'person has', plural: 'people have')} tried it." : ""
    description = "#{item.current_version.stem.truncate(160)}#{tried}"
    url = "#{request.base_url}/q/#{item.public_id}"
    image = "#{request.base_url}/og.png"
    {
      "og:type" => "website", "og:site_name" => "Questionize", "og:title" => title, "og:description" => description,
      "og:url" => url, "og:image" => image, "twitter:card" => "summary_large_image", "twitter:title" => title,
      "twitter:description" => description, "twitter:image" => image
    }.map { |key, value| tag.meta(**{ (key.start_with?("og:") ? :property : :name) => key, content: value }) }
     .unshift(tag.title(title))
     .join("\n")
  end

  def tag
    helpers.tag
  end
end
