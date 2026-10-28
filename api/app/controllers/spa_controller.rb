# Serves the Vue web app's shell for client-side routes (/, /snap, /questions, /me, ...).
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

  # The image ships the shell as app.html so the static file server (which caches for a year)
  # never answers "/" with it: a stale shell would point at assets the next deploy removed.
  def index_html
    response.headers["Cache-Control"] = "no-cache"
    path = [ "app.html", "index.html" ].map { Rails.public_path.join(_1) }.find(&:exist?)
    path ? path.read : FALLBACK
  end
end
