module Api
  module V1
    # First launch of a client: an anonymous user and its bearer token.
    class DevicesController < BaseController
      skip_before_action :authenticate!
      rate_limit to: 10, within: 1.hour, only: :create

      def create
        user = User.create!(anonymous: true)
        render json: { token: user.api_token, user: { handle: user.handle, xp: user.xp } }, status: :created
      end
    end
  end
end
