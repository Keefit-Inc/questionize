module Research
  class MemoryVersion < ApplicationRecord
    belongs_to :parent, class_name: "Research::MemoryVersion", optional: true
    before_validation :identify, on: :create
    validates :public_id, :content_hash, :payload_ciphertext, presence: true
    validates :version, uniqueness: true, numericality: { only_integer: true, greater_than: 0 }
    validate :check_payload
    validate :immutable, on: :update

    def self.encryptor
      key = Rails.application.key_generator.generate_key("research/private-memory/v1", 32)
      ActiveSupport::MessageEncryptor.new(key, cipher: "aes-256-gcm")
    end

    def payload=(value)
      self.content_hash = Research.digest(value)
      self.payload_ciphertext = self.class.encryptor.encrypt_and_sign(value)
    end

    def payload
      self.class.encryptor.decrypt_and_verify(payload_ciphertext) if payload_ciphertext.present?
    end

    def context
      { "id" => public_id, "version" => version, "hash" => content_hash, "payload" => payload }
    end

    def public_data
      { id: public_id, version: version, content_hash: content_hash, parent_version: parent&.version,
        expert_rules: Array(payload["expert_rules"]).size, experience_rules: Array(payload["experience_rules"]).size }
    end

    private

    def identify
      self.public_id ||= SecureRandom.hex(8)
    end

    def check_payload
      p = payload
      valid = p.is_a?(Hash) && p.keys.sort == %w[experience_rules expert_rules] && p.values.all? { _1.is_a?(Array) && _1.size <= 4 && _1.all? { |r| r.is_a?(String) && r.size.between?(1, 280) } }
      errors.add(:payload, "requires two bounded, separate rule namespaces") unless valid
      errors.add(:content_hash, "does not match payload") if valid && content_hash != Research.digest(p)
    end

    def immutable
      errors.add(:base, "memory versions are immutable") if changes_to_save.except("updated_at").any?
    end
  end
end
