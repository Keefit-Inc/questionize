module Auth
  # Verifies a Facebook Login access token from the browser and reads the profile fields the
  # learner agreed to share. Also checks the signed requests Facebook sends for data deletion.
  class Facebook
    class Error < StandardError; end

    Profile = Data.define(:uid, :name, :email)

    # Tests replace the Graph API with a lambda (path, params) -> parsed JSON.
    class_attribute :graph_client

    def self.configured?
      config.app_id.present? && config.app_secret.present?
    end

    def self.config
      Rails.application.config.x.facebook
    end

    def initialize(http: nil)
      @http = http || self.class.graph_client || method(:get_json)
    end

    # The token must have been issued to our app, be valid, and belong to the user it describes.
    def profile(access_token)
      raise Error, "Facebook Login is not configured" unless self.class.configured?

      debug = @http.call("/debug_token", input_token: access_token, access_token: "#{config.app_id}|#{config.app_secret}")
      data = debug.fetch("data", {})
      raise Error, "token not valid for this app" unless data["is_valid"] && data["app_id"].to_s == config.app_id.to_s

      me = @http.call("/me", fields: "id,name,email", access_token: access_token,
                             appsecret_proof: OpenSSL::HMAC.hexdigest("SHA256", config.app_secret, access_token))
      raise Error, "token belongs to another user" unless me["id"].to_s == data["user_id"].to_s

      Profile.new(uid: me["id"].to_s, name: me["name"], email: me["email"])
    end

    # Facebook's signed_request: base64url(signature).base64url(payload), HMAC-SHA256 with the app secret.
    def self.parse_signed_request(signed_request)
      raise Error, "Facebook Login is not configured" unless configured?

      encoded_sig, payload = signed_request.to_s.split(".", 2)
      raise Error, "malformed signed request" if encoded_sig.blank? || payload.blank?

      expected = OpenSSL::HMAC.digest("SHA256", config.app_secret, payload)
      raise Error, "bad signature" unless ActiveSupport::SecurityUtils.secure_compare(Base64.urlsafe_decode64(pad(encoded_sig)), expected)

      JSON.parse(Base64.urlsafe_decode64(pad(payload)))
    rescue ArgumentError, JSON::ParserError
      raise Error, "malformed signed request"
    end

    def self.pad(s) = s + "=" * ((4 - s.length % 4) % 4)

    private

    def config = self.class.config

    def get_json(path, params)
      uri = URI("#{config.graph_url}#{path}")
      uri.query = URI.encode_www_form(params)
      response = Net::HTTP.start(uri.host, uri.port, use_ssl: uri.scheme == "https", open_timeout: 5, read_timeout: 10) { _1.get(uri.request_uri) }
      body = JSON.parse(response.body)
      raise Error, body.dig("error", "message") || "Facebook returned #{response.code}" unless response.is_a?(Net::HTTPSuccess)

      body
    rescue JSON::ParserError, SocketError, Timeout::Error, Errno::ECONNREFUSED => e
      raise Error, e.message
    end
  end
end
