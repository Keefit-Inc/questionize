module Api
  module V1
    # GET /api/v1/me — the learner's own profile: XP and ratings by skill.
    class MeController < BaseController
      PROVISIONAL_BELOW = 10

      def show
        ratings = current_user.skill_ratings.order(:skill).map do |r|
          { skill: r.skill, rating: r.rating.round, attempts: r.attempts, correct: r.correct,
            provisional: r.attempts < PROVISIONAL_BELOW }
        end
        render json: { handle: current_user.handle, anonymous: current_user.anonymous, xp: current_user.xp, ratings: ratings }
      end
    end
  end
end
