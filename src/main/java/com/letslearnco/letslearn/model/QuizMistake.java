package com.letslearnco.letslearn.model;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "quiz_mistakes", indexes = {
        @Index(name = "idx_mistakes_file_md5", columnList = "file_md5"),
        @Index(name = "idx_mistakes_user_file", columnList = "user_id, file_md5")
})
public class QuizMistake {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "file_md5", nullable = false, length = 64)
    private String fileMd5;

    @Column(name = "quiz_id")
    private Long quizId;

    @Column(name = "card_title", length = 255)
    private String cardTitle;

    @Column(name = "explanation", columnDefinition = "TEXT")
    private String explanation;

    @Column(name = "question", columnDefinition = "TEXT")
    private String question;

    @Column(name = "options_json", columnDefinition = "TEXT")
    private String optionsJson;

    @Column(name = "correct_label", length = 4)
    private String correctLabel;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
