module Research
  def self.table_name_prefix = "research_"

  def self.digest(value)
    Digest::SHA256.hexdigest(JSON.generate(canonical(value)))
  end

  def self.canonical(value)
    case value
    when Hash then value.sort.to_h.transform_values { canonical(_1) }
    when Array then value.map { canonical(_1) }
    else value
    end
  end
end
