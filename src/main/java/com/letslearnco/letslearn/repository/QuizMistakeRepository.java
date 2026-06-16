package com.letslearnco.letslearn.repository;

import com.letslearnco.letslearn.model.QuizMistake;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Repository
public interface QuizMistakeRepository extends JpaRepository<QuizMistake, Long> {

    List<QuizMistake> findByFileMd5AndUserId(String fileMd5, Long userId);

    @Modifying
    @Transactional
    void deleteByFileMd5AndUserId(String fileMd5, Long userId);
}
