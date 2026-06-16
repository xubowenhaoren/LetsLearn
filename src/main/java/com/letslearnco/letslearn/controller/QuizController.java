package com.letslearnco.letslearn.controller;

import com.letslearnco.letslearn.model.QuizMistake;
import com.letslearnco.letslearn.model.QuizSession;
import com.letslearnco.letslearn.model.User;
import com.letslearnco.letslearn.repository.QuizMistakeRepository;
import com.letslearnco.letslearn.repository.QuizSessionRepository;
import com.letslearnco.letslearn.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

@RestController
@RequestMapping("/api/v1/quiz")
public class QuizController {

    @Autowired
    private QuizSessionRepository quizSessionRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private QuizMistakeRepository quizMistakeRepository;


    private Long resolveUserId(@RequestAttribute(value = "userId", required = false) String jwtUserId,
                               @RequestParam(value = "userId", required = false) String paramUserId) {
        if (paramUserId != null && !paramUserId.isEmpty()) return Long.valueOf(paramUserId);
        if (jwtUserId != null) return Long.valueOf(jwtUserId);
        return 1L; // fallback admin
    }

    @PostMapping("/save")
    public ResponseEntity<Map<String, Object>> saveQuiz(
            @RequestBody Map<String, Object> body,
            @RequestAttribute(value = "userId", required = false) String jwtUserId,
            @RequestParam(value = "userId", required = false) String paramUserId) {
        Long userId = resolveUserId(jwtUserId, paramUserId);

        User user = userRepository.findById(Long.valueOf(userId)).orElse(null);
        if (user == null) {
            return ResponseEntity.badRequest().body(Map.of("message", "User not found"));
        }

        QuizSession session = new QuizSession();
        session.setUser(user);
        session.setFileMd5((String) body.get("fileMd5"));
        session.setFileName((String) body.get("fileName"));
        session.setCardsJson(toString(body.get("cards")));
        session.setUserAnswersJson(toString(body.get("userAnswers")));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> answers = (List<Map<String, Object>>) body.getOrDefault("userAnswers", List.of());
        int total = answers.size();
        long correct = answers.stream().filter(a -> Boolean.TRUE.equals(a.get("isCorrect"))).count();
        session.setTotalCount(total);
        session.setCorrectCount((int) correct);
        session.setAccuracy(total > 0
                ? BigDecimal.valueOf(correct * 100.0 / total).setScale(2, RoundingMode.HALF_UP)
                : BigDecimal.ZERO);

        quizSessionRepository.save(session);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("quizId", session.getId());
        result.put("message", "Quiz saved successfully");
        return ResponseEntity.ok(result);
    }

    @GetMapping("/latest")
    public ResponseEntity<Map<String, Object>> getLatestQuiz(
            @RequestParam String fileMd5,
            @RequestAttribute(value = "userId", required = false) String jwtUserId,
            @RequestParam(value = "userId", required = false) String paramUserId) {
        Long userId = resolveUserId(jwtUserId, paramUserId);

        List<QuizSession> sessions = quizSessionRepository.findLatestByUserIdAndFileMd5(
                Long.valueOf(userId), fileMd5);

        if (sessions.isEmpty()) {
            return ResponseEntity.ok(Map.of("hasQuiz", false));
        }

        QuizSession qs = sessions.get(0);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("hasQuiz", true);
        result.put("quizId", qs.getId());
        result.put("fileMd5", qs.getFileMd5());
        result.put("fileName", qs.getFileName());
        result.put("cardsJson", qs.getCardsJson());
        result.put("userAnswersJson", qs.getUserAnswersJson());
        result.put("correctCount", qs.getCorrectCount());
        result.put("totalCount", qs.getTotalCount());
        result.put("accuracy", qs.getAccuracy());
        result.put("createdAt", qs.getCreatedAt() != null ? qs.getCreatedAt().toString() : null);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/check")
    public ResponseEntity<Map<String, Object>> checkQuiz(
            @RequestParam String fileMd5,
            @RequestAttribute(value = "userId", required = false) String jwtUserId,
            @RequestParam(value = "userId", required = false) String paramUserId) {
        Long userId = resolveUserId(jwtUserId, paramUserId);

        boolean exists = quizSessionRepository.existsByUserIdAndFileMd5(Long.valueOf(userId), fileMd5);
        return ResponseEntity.ok(Map.of("hasQuiz", exists));
    }

    @GetMapping("/history")
    public ResponseEntity<List<Map<String, Object>>> getHistory(
            @RequestParam String fileMd5,
            @RequestAttribute(value = "userId", required = false) String jwtUserId,
            @RequestParam(value = "userId", required = false) String paramUserId) {
        Long userId = resolveUserId(jwtUserId, paramUserId);

        List<QuizSession> sessions = quizSessionRepository.findByUserIdAndFileMd5OrderByCreatedAtDesc(
                Long.valueOf(userId), fileMd5);

        List<Map<String, Object>> result = new ArrayList<>();
        for (QuizSession qs : sessions) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("quizId", qs.getId());
            item.put("correctCount", qs.getCorrectCount());
            item.put("totalCount", qs.getTotalCount());
            item.put("accuracy", qs.getAccuracy());
            item.put("createdAt", qs.getCreatedAt() != null ? qs.getCreatedAt().toString() : null);
            result.add(item);
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/detail")
    public ResponseEntity<Map<String, Object>> getDetail(
            @RequestParam Long quizId,
            @RequestAttribute(value = "userId", required = false) String jwtUserId,
            @RequestParam(value = "userId", required = false) String paramUserId) {
        Long userId = resolveUserId(jwtUserId, paramUserId);

        Optional<QuizSession> opt = quizSessionRepository.findById(quizId);
        if (opt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        QuizSession qs = opt.get();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("quizId", qs.getId());
        result.put("fileMd5", qs.getFileMd5());
        result.put("fileName", qs.getFileName());
        result.put("cardsJson", qs.getCardsJson());
        result.put("userAnswersJson", qs.getUserAnswersJson());
        result.put("correctCount", qs.getCorrectCount());
        result.put("totalCount", qs.getTotalCount());
        result.put("accuracy", qs.getAccuracy());
        result.put("createdAt", qs.getCreatedAt() != null ? qs.getCreatedAt().toString() : null);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/save-mistakes")
    @Transactional
    public ResponseEntity<Map<String, Object>> saveMistakes(
            @RequestBody Map<String, Object> body,
            @RequestAttribute(value = "userId", required = false) String jwtUserId,
            @RequestParam(value = "userId", required = false) String paramUserId) {
        Long userId = resolveUserId(jwtUserId, paramUserId);

        User user = userRepository.findById(Long.valueOf(userId)).orElse(null);
        if (user == null) return ResponseEntity.badRequest().body(Map.of("message", "User not found"));

        String fileMd5 = (String) body.get("fileMd5");
        Long quizId = body.get("quizId") != null ? Long.valueOf(body.get("quizId").toString()) : null;

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> mistakes = (List<Map<String, Object>>) body.getOrDefault("mistakes", List.of());

        // Replace old mistakes for this file+user with new batch
        quizMistakeRepository.deleteByFileMd5AndUserId(fileMd5, Long.valueOf(userId));

        for (Map<String, Object> m : mistakes) {
            QuizMistake qm = new QuizMistake();
            qm.setUser(user);
            qm.setFileMd5(fileMd5);
            qm.setQuizId(quizId);
            qm.setCardTitle((String) m.get("title"));
            qm.setExplanation((String) m.get("aiExplanation"));
            qm.setQuestion((String) m.get("question"));
            qm.setOptionsJson(toString(m.get("options")));
            qm.setCorrectLabel((String) m.get("correctLabel"));
            quizMistakeRepository.save(qm);
        }

        return ResponseEntity.ok(Map.of("message", "Mistakes saved", "count", mistakes.size()));
    }

    @GetMapping("/mistakes")
    public ResponseEntity<Map<String, Object>> getMistakes(
            @RequestParam String fileMd5,
            @RequestAttribute(value = "userId", required = false) String jwtUserId,
            @RequestParam(value = "userId", required = false) String paramUserId) {
        Long userId = resolveUserId(jwtUserId, paramUserId);

        List<QuizMistake> list = quizMistakeRepository.findByFileMd5AndUserId(fileMd5, Long.valueOf(userId));
        if (list.isEmpty()) {
            return ResponseEntity.ok(Map.of("hasMistakes", false));
        }

        List<Map<String, Object>> cards = new ArrayList<>();
        for (QuizMistake qm : list) {
            Map<String, Object> card = new LinkedHashMap<>();
            card.put("title", qm.getCardTitle());
            card.put("aiExplanation", qm.getExplanation());
            card.put("question", qm.getQuestion());
            card.put("correctLabel", qm.getCorrectLabel());
            try {
                card.put("options", new com.fasterxml.jackson.databind.ObjectMapper().readValue(
                        qm.getOptionsJson() != null ? qm.getOptionsJson() : "[]", List.class));
            } catch (Exception e) {
                card.put("options", List.of());
            }
            cards.add(card);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("hasMistakes", true);
        result.put("mistakes", cards);
        return ResponseEntity.ok(result);
    }

    private String toString(Object obj) {
        if (obj instanceof String s) return s;
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(obj);
        } catch (Exception e) {
            return "[]";
        }
    }
}
