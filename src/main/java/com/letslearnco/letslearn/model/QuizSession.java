package com.letslearnco.letslearn.model;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "quiz_sessions", indexes = {
        @Index(name = "idx_quiz_user_file", columnList = "user_id, file_md5"),
        @Index(name = "idx_quiz_created", columnList = "created_at")
})
public class QuizSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "file_md5", nullable = false, length = 64)
    private String fileMd5;

    @Column(name = "file_name", length = 255)
    private String fileName;

    @Column(name = "cards_json", columnDefinition = "LONGTEXT")
    private String cardsJson;

    @Column(name = "user_answers_json", columnDefinition = "LONGTEXT")
    private String userAnswersJson;

    @Column(name = "correct_count")
    private Integer correctCount;

    @Column(name = "total_count")
    private Integer totalCount;

    @Column(name = "accuracy", precision = 5, scale = 2)
    private java.math.BigDecimal accuracy;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
