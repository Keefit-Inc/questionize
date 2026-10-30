module Research
  class WorkerCredential < ApplicationRecord
    validates :name, :token_digest, presence: true
    def self.authenticate(token)
      return if token.blank?

      find_by(token_digest: Digest::SHA256.hexdigest(token), revoked_at: nil)
    end
  end
end
