module Api
  module V1
    # GET /api/v1/me — the learner's own profile: XP, ratings by skill, linked sign-in.
    # DELETE /api/v1/me — deletes the account and everything personal in it.
    class MeController < BaseController
      PROVISIONAL_BELOW = 10

      def show
        ratings = current_user.skill_ratings.order(:skill).map do |r|
          { skill: r.skill, rating: r.rating.round, attempts: r.attempts, correct: r.correct,
            provisional: r.attempts < PROVISIONAL_BELOW }
        end
        identity = current_user.identities.first
        render json: { handle: current_user.handle, anonymous: current_user.anonymous, xp: current_user.xp, ratings: ratings,
                       account: identity && { provider: identity.provider, name: identity.name } }
      end

      # Shared questions the learner helped create stay in the bank (they hold nothing personal);
      # answers already counted in crowd tallies stay as anonymous counts.
      def destroy
        current_user.destroy!
        head :no_content
      end
    end
  end
end
