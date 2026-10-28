module Auth
  # Signs a learner in with a provider account. A new account is linked to the device's current
  # user, so nothing they did anonymously is lost. If the provider account already belongs to
  # another user, this device switches to that user and brings along its snapped questions and
  # review list; ratings stay with the account they were earned on.
  class LinkIdentity
    Result = Data.define(:user, :switched)

    def self.call(...) = new(...).call

    def initialize(current_user:, provider:, profile:)
      @current = current_user
      @provider = provider
      @profile = profile
    end

    def call
      ApplicationRecord.transaction do
        identity = UserIdentity.find_by(provider: @provider, uid: @profile.uid)
        if identity.nil?
          @current.identities.create!(provider: @provider, uid: @profile.uid, name: @profile.name, email: @profile.email)
          @current.update!(anonymous: false)
          Result.new(user: @current, switched: false)
        elsif identity.user_id == @current.id
          identity.update!(name: @profile.name, email: @profile.email)
          Result.new(user: @current, switched: false)
        else
          bring_over(@current, identity.user) if @current.anonymous && @current.identities.none?
          Result.new(user: identity.user, switched: true)
        end
      end
    end

    private

    def bring_over(from, to)
      from.error_log_entries.update_all(user_id: to.id)
      GenerationRun.where(user: from).update_all(user_id: to.id)
      taken = to.saved_items.pluck(:item_id)
      from.saved_items.where.not(item_id: taken).update_all(user_id: to.id)
    end
  end
end
