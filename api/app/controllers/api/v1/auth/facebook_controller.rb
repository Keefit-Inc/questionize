module Api
  module V1
    module Auth
      # Facebook Login (docs/ARCHITECTURE.md §5.7).
      class FacebookController < BaseController
        skip_before_action :authenticate!, only: :data_deletion
        rate_limit to: 20, within: 10.minutes, only: :create, by: -> { current_user.id }

        # POST /api/v1/auth/facebook {access_token}
        # Links the Facebook account to this device's user (or switches to the user it belongs to)
        # and returns the bearer token to use from now on.
        def create
          profile = ::Auth::Facebook.new.profile(params.require(:access_token).to_s)
          result = ::Auth::LinkIdentity.call(current_user: current_user, provider: "facebook", profile: profile)
          render json: { token: result.user.api_token, switched: result.switched,
                         user: { handle: result.user.handle, xp: result.user.xp, account: { provider: "facebook", name: profile.name } } }
        rescue ::Auth::Facebook::Error => e
          Rails.logger.warn("[facebook] #{e.message}")
          render json: { error: "facebook_login_failed" }, status: :unauthorized
        end

        # POST /api/v1/auth/facebook/data_deletion {signed_request}
        # Facebook's data deletion callback: someone removed Questionize from their Facebook
        # settings and asked for their data to be deleted.
        def data_deletion
          payload = ::Auth::Facebook.parse_signed_request(params.require(:signed_request))
          identity = UserIdentity.find_by(provider: "facebook", uid: payload["user_id"].to_s)
          identity&.user&.destroy!
          code = SecureRandom.hex(8)
          render json: { url: "#{request.base_url}/data-deletion?code=#{code}", confirmation_code: code }
        rescue ::Auth::Facebook::Error
          render json: { error: "invalid_request" }, status: :bad_request
        end
      end
    end
  end
end
