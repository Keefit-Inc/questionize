module Api
  module V1
    # JSON API used by the extension and web app. Clients authenticate with the bearer
    # token issued by POST /api/v1/devices.
    class BaseController < ActionController::API
      include ActionController::HttpAuthentication::Token::ControllerMethods

      before_action :authenticate!

      rescue_from ActiveRecord::RecordNotFound do
        render json: { error: "not_found" }, status: :not_found
      end

      private

      attr_reader :current_user

      def authenticate!
        @current_user = authenticate_with_http_token { |token, _| User.find_by(api_token: token) }
        render json: { error: "unauthorized" }, status: :unauthorized unless @current_user
      end
    end
  end
end
