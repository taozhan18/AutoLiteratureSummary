from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os

def create_sample_pdf():
    """创建示例PDF文件用于测试"""
    # 确保sample_pdfs目录存在
    os.makedirs("sample_pdfs", exist_ok=True)
    
    # 创建示例PDF内容
    sample_texts = [
        {
            "filename": "sample_research_paper_1.pdf",
            "title": "Deep Learning Approaches for Natural Language Processing",
            "content": """
            Abstract: This paper presents a comprehensive review of deep learning approaches in natural language processing. 
            We examine various neural network architectures and their applications in text classification, machine translation, 
            and sentiment analysis. Our experiments show significant improvements over traditional methods.
            
            Introduction: Natural language processing (NLP) has witnessed revolutionary changes with the advent of deep learning. 
            Traditional feature engineering approaches have been largely replaced by neural models that can automatically 
            learn representations from raw text data.
            
            Methods: We evaluated several deep learning models including recurrent neural networks (RNNs), long short-term memory 
            networks (LSTMs), and transformer architectures on standard benchmark datasets.
            
            Results: Our findings indicate that transformer-based models consistently outperform other architectures across 
            multiple NLP tasks, with an average improvement of 5-10% in accuracy metrics.
            
            Conclusion: Deep learning has fundamentally transformed NLP research and applications. Future work should focus 
            on improving model interpretability and reducing computational requirements.
            """
        },
        {
            "filename": "sample_research_paper_2.pdf",
            "title": "Computer Vision Techniques for Medical Image Analysis",
            "content": """
            Abstract: This study explores the application of computer vision techniques in medical image analysis. 
            We propose a novel convolutional neural network architecture for detecting anomalies in radiological images.
            
            Introduction: Medical imaging plays a crucial role in modern healthcare diagnostics. The increasing volume 
            of medical images necessitates automated analysis tools to assist healthcare professionals.
            
            Methods: Our approach combines traditional image processing techniques with deep convolutional neural networks. 
            We trained our model on a dataset of 10,000 radiological images from multiple medical institutions.
            
            Results: The proposed method achieved 94.2% accuracy in anomaly detection, outperforming existing approaches 
            by a significant margin. False positive rate was reduced to 3.1%.
            
            Conclusion: Computer vision techniques show great promise in medical applications. Integration with clinical 
            workflows requires careful consideration of safety and regulatory requirements.
            """
        }
    ]
    
    # 生成PDF文件
    styles = getSampleStyleSheet()
    
    for sample in sample_texts:
        doc = SimpleDocTemplate(f"sample_pdfs/{sample['filename']}", pagesize=letter)
        story = []
        
        # 添加标题
        title = Paragraph(sample['title'], styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # 添加内容
        content = Paragraph(sample['content'], styles['Normal'])
        story.append(content)
        
        # 构建PDF
        doc.build(story)
        print(f"已创建示例PDF文件: {sample['filename']}")

if __name__ == "__main__":
    try:
        import reportlab
        create_sample_pdf()
    except ImportError:
        print("未安装reportlab库，无法创建示例PDF文件")
        print("如需创建示例文件，请运行: pip install reportlab")