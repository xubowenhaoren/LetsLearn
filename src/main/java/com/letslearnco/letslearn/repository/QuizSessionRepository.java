package com.letslearnco.letslearn.repository;

import com.letslearnco.letslearn.model.QuizSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface QuizSessionRepository extends JpaRepository<QuizSession, Long> {

    List<QuizSession> findByUserIdAndFileMd5OrderByCreatedAtDesc(Long userId, String fileMd5);

    @Query("SELECT qs FROM QuizSession qs WHERE qs.user.id = :userId AND qs.fileMd5 = :fileMd5 ORDER BY qs.createdAt DESC")
    List<QuizSession> findLatestByUserIdAndFileMd5(@Param("userId") Long userId, @Param("fileMd5") String fileMd5);

    boolean existsByUserIdAndFileMd5(Long userId, String fileMd5);
}
