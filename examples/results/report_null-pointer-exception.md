# Relatório de Diagnóstico: null-pointer-exception.log

**Modo de Diagnóstico:** fallback
**Status:** success_fallback

## Resumo
Diagnóstico gerado em modo fallback devido a falha na IA ou ausência de chave.

## Detalhes
- **Categoria:** Code
- **Severidade:** high
- **Exceção Principal:** java.lang.NullPointerException: Cannot invoke "com.example.model.User.getName()" because "user" is null

## Causa Provável
Exceção principal detectada: java.lang.NullPointerException: Cannot invoke "com.example.model.User.getName()" because "user" is null

## Evidências
- `java.lang.NullPointerException: Cannot invoke "com.example.model.User.getName()" because "user" is null`
- `2026-07-18 11:20:05.115 ERROR 54321 --- [http-nio-8080-exec-1] c.e.c.GlobalExceptionHandler : Unhandled exception occurred`

## Recomendações
- Verificar a stack trace completa no arquivo de log original.
- Configurar chave de API válida para diagnóstico avançado com IA.
