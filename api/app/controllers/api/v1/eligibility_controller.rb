module Api
  module V1
    # POST /api/v1/me/eligibility {country, age_13_plus}
    # Photo capture launches in the United States for users 13 and older.
    class EligibilityController < BaseController
      def create
        country = params.require(:country).to_s.upcase
        return render(json: { error: "invalid_country" }, status: :unprocessable_entity) unless country.match?(/\A[A-Z]{2}\z/)

        current_user.update!(country_code: country, age_confirmed_at: ActiveModel::Type::Boolean.new.cast(params[:age_13_plus]) ? Time.current : nil)
        render json: { country: current_user.country_code, error_log: current_user.error_log_eligible? }
      end
    end
  end
end
