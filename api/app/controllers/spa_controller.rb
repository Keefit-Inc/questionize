# Serves the Vue web app's index.html for client-side routes (/me, /feed, ...).
# Share pages (/q/:id) go through SharePagesController to get social preview tags first.
class SpaController < ActionController::Base
  FALLBACK = <<~HTML.freeze
    <!doctype html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Questionize</title></head>
    <body><div id="app"></div></body></html>
  HTML

  def show
    render html: index_html.html_safe, layout: false # static build output, no user content
  end

  private

  def index_html
    path = Rails.public_path.join("index.html")
    path.exist? ? path.read : FALLBACK
  end
end
