package com.letslearnco.letslearn.repository;

import com.letslearnco.letslearn.model.RateLimitConfig;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RateLimitConfigRepository extends JpaRepository<RateLimitConfig, String> {
}
