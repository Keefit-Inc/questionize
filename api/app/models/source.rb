class Source < ApplicationRecord
  TRACKING_PARAMS = /\A(utm_\w+|fbclid|gclid|mc_cid|mc_eid|ref|ref_src|cmpid|smid)\z/i

  has_many :items, dependent: :nullify
  validates :canonical_url, presence: true, uniqueness: true

  # The same article under different tracking links maps to one source.
  def self.canonicalize(url)
    uri = URI.parse(url.to_s.strip)
    raise URI::InvalidURIError, "not an http(s) URL" unless uri.is_a?(URI::HTTP) && uri.host.present?

    uri.scheme = "https"
    uri.host = uri.host.downcase.delete_prefix("www.")
    uri.fragment = nil
    uri.port = nil if [ 80, 443 ].include?(uri.port)
    params = URI.decode_www_form(uri.query.to_s).reject { |key, _| key.match?(TRACKING_PARAMS) }.sort
    uri.query = params.empty? ? nil : URI.encode_www_form(params)
    uri.path = uri.path.delete_suffix("/") if uri.path.length > 1
    uri.to_s
  end

  def self.for_page!(url:, title:, text:)
    canonical = canonicalize(url)
    source = find_by(canonical_url: canonical) || create!(canonical_url: canonical, domain: URI(canonical).host)
    source.update!(title: title.presence || source.title, content_hash: Digest::SHA256.hexdigest(text.to_s.squish))
    source
  rescue ActiveRecord::RecordNotUnique
    retry # a concurrent request created it first
  end
end
