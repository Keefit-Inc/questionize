module Api
  module V1
    # GET /api/v1/config — public client settings that change without a rebuild.
    class ConfigController < BaseController
      skip_before_action :authenticate!

      def show
        render json: { facebook_app_id: ::Auth::Facebook.configured? ? ::Auth::Facebook.config.app_id : nil }
      end
    end
  end
end
