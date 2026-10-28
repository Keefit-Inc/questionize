require "net/http"

module AiService
  # Calls the internal AI service: NDJSON streams (/v1/generate, /v1/map) and JSON (/v1/review).
  class Client
    def initialize(url: Rails.configuration.x.ai_service.url, token: Rails.configuration.x.ai_service.token,
                   read_timeout: Rails.configuration.x.ai_service.read_timeout)
      @base = URI(url)
      @token = token
      @read_timeout = read_timeout
    end

    def generate(payload, &block)
      stream("/v1/generate", payload, &block)
    end

    def map(payload, &block)
      stream("/v1/map", payload, &block)
    end

    # POST /v1/review returns one JSON document.
    def review(payload)
      body = +""
      post("/v1/review", payload) { |response| response.read_body { |chunk| body << chunk } }
      JSON.parse(body)
    rescue JSON::ParserError => e
      raise Error, "AI service returned invalid JSON: #{e.message}"
    end

    private

    def stream(path, payload)
      post(path, payload) do |response|
        buffer = +""
        response.read_body do |chunk|
          buffer << chunk
          while (newline = buffer.index("\n"))
            line = buffer.slice!(0..newline).strip
            yield JSON.parse(line) unless line.empty?
          end
        end
        yield JSON.parse(buffer) unless buffer.strip.empty?
      end
    rescue JSON::ParserError => e
      raise Error, "AI service request failed: #{e.class}: #{e.message}"
    end

    def post(path, payload)
      uri = URI.join(@base, path)
      request = Net::HTTP::Post.new(uri, "Content-Type" => "application/json", "X-Internal-Token" => @token)
      request.body = JSON.generate(payload)

      Net::HTTP.start(uri.host, uri.port, use_ssl: uri.scheme == "https", read_timeout: @read_timeout, open_timeout: 10) do |http|
        http.request(request) do |response|
          raise Error, "AI service returned #{response.code}: #{response.body.to_s.truncate(300)}" unless response.is_a?(Net::HTTPSuccess)

          yield response
        end
      end
    rescue SystemCallError, IOError, Timeout::Error, Net::OpenTimeout, Net::ReadTimeout => e
      raise Error, "AI service request failed: #{e.class}: #{e.message}"
    end
  end
end
