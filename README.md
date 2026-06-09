# MACSpep Single Peptides Scraper

Miltenyi Biotec 웹사이트에서 MACSpep Single Peptides 데이터를 자동으로 수집하는 웹 스크래퍼입니다.

## 🎯 주요 기능

- **자동 제품 로드**: "Load 25 More" 버튼 자동 클릭
- **아코디언 확장**: 모든 제품 그룹 아코디언 자동 확장
- **Allele 처리**: 각 제품의 모든 MHC allele 옵션 처리
- **다중 Datasheet 수집**: 각 allele별 모든 데이터시트 수집
- **PDF 파싱**: 각 데이터시트에서 다음 정보 추출:
  - Antigen
  - Peptide Sequence
  - Main MHC Allele
  - Further MHC Alleles
- **CSV 출력**: 정리된 데이터를 CSV로 저장

## 📊 결과

- **310개 레코드** 수집
- **74개 unique antigen**
- **43개 unique MHC alleles**
- **100% 데이터 완성도**

## 🛠️ 설치

### 필요 사항
- Python 3.7+
- Chrome 브라우저

### 설정

```bash
# 저장소 클론
git clone https://github.com/yourusername/macspep-scraper.git
cd macspep-scraper

# 의존성 설치
pip install -r requirements.txt
```

## 🚀 사용법

```bash
# 기본 실행 (기본 URL 사용)
python3 macspep_scraper.py

# 커스텀 URL 지정
python3 macspep_scraper.py --url "https://..." --output "output.csv"

# 옵션
python3 macspep_scraper.py --help
```

## 📋 출력 CSV 구조

```
antigen,peptide_sequence,main_mhc_allele,further_mhc_alleles,datasheet_url
CEACAM1,NPVEDKDAVAF,HLA-B*35,"B*35:01, B*35:03",https://...
CEACAM1,LPVSPRLQL,HLA-B*07,B*07:02,https://...
...
```

## 🔍 Workflow

### Phase 1: 제품 목록 로드
- 리스팅 페이지 열기
- "Load 25 More" 버튼 자동 클릭
- 모든 제품이 로드될 때까지 반복

### Phase 2: 아코디언 확장 및 제품 링크 수집
- 모든 제품 그룹 아코디언 확장
- 각 아코디언 내 개별 제품 링크 수집

### Phase 3: Allele 처리 및 Datasheet 수집
- 각 제품 페이지 방문
- "Select a allele" 버튼으로 모든 allele 옵션 처리
- 각 allele별 모든 visible datasheet 링크 수집

### Phase 4: PDF 다운로드 및 파싱
- 각 datasheet PDF 다운로드
- PDF에서 필드 추출:
  - Antigen
  - Peptide Sequence
  - Main MHC Allele
  - Further MHC Alleles

### Phase 5: CSV 저장
- 추출된 데이터를 CSV로 정렬하여 저장

## 📊 로깅

스크래퍼는 다음 메트릭을 자동으로 추적합니다:

- Load 25 More 클릭 횟수
- 확장된 제품 그룹 수
- 수집된 제품 URL 수
- 처리된 Allele 옵션 수
- 수집된 Datasheet URL 수
- 파싱된 PDF 수
- 최종 CSV 크기

## ⚠️ 주의사항

- 스크래퍼는 느릴 수 있습니다 (각 제품당 여러 allele 처리)
- 대역폭 낭비를 피하기 위해 적절한 대기 시간을 포함합니다
- 웹사이트 구조 변경 시 수정이 필요할 수 있습니다

## 📝 라이선스

MIT License

## 👨‍💻 작성자

sbpark@target.re.kr

## 🤝 기여

개선 사항이나 버그 리포트는 이슈를 통해 공유해주세요.
