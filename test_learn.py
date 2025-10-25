# mental_health_agent.py
from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low
from typing import Dict, List, Optional, Tuple
import json
import re
from datetime import datetime, timedelta
import asyncio

# Data Models
class ChildMessage(Model):
    message: str
    age: Optional[int] = None
    session_id: str
    timestamp: str

class AgentResponse(Model):
    response: str
    concerns_detected: List[str] = []
    follow_up_needed: bool = False
    safety_alert: bool = False
    session_id: str

class ConversationAnalysis(Model):
    session_id: str
    risk_level: str
    topics_discussed: List[str]
    recommendations: List[str]
    timestamp: str

# Initialize the agent
mental_health_agent = Agent(
    name="child_mental_health_support",
    port=8000,
    endpoint=["http://localhost:8000/submit"],
    seed="child_mental_health_agent_seed_123"
)

fund_agent_if_low(mental_health_agent.wallet.address())

# Your structured data implementation
class MentalHealthKnowledgeBase:
    def __init__(self):
        # Q&A Pairs for Symptom Elicitation
        self.qa_pairs = [
            {"intent": "initiate_connection", "user_prompt_context": "start_of_conversation", "agent_response": "Hi, I love you and care about you. What's the best way to regularly connect about mental health and wellness?"},
            {"intent": "stress_check", "user_says": "I'm stressed about homework.", "agent_response": "It sounds like you have a lot on your plate. What's your favorite way to relax or de-stress?"},
            {"intent": "behavioral_probe", "user_says": "I feel tired all the time.", "agent_response": "That sounds draining. What has been taking up most of your mental energy these days?"},
            {"intent": "anxiety_probe", "user_says": "I'm worried about the future.", "agent_response": "It sounds like the future is causing you some worries. Do you feel anxious? If so, what leads to that feeling, and what does anxiety feel like to you?"},
            {"intent": "validate_and_offer_choice", "user_says": "I'm sad today.", "agent_response": "It sounds like you're feeling really sad. Would you like me to just listen, or could I share some ideas I have?"},
            {"intent": "positive_alternative", "user_says": "I hate that I'm always running inside.", "agent_response": "Instead of focusing on 'stopping,' let's think about alternatives. Running is for outside and walking is for inside. Which do you want to start with?"}
        ]
        
        # Ethical Guardrails
        self.ethical_guardrails = [
            {"rule_type": "stigmatizing_language", "avoid_pattern": "brain disorder", "best_practice": "mental health condition"},
            {"rule_type": "stigmatizing_language", "avoid_pattern": "is schizophrenic", "best_practice": "has schizophrenia"},
            {"rule_type": "stigmatizing_language", "avoid_pattern": "suffers from", "best_practice": "lives with"},
            {"rule_type": "scope_limitation", "avoid_pattern": "diagnose", "best_practice": "support and recommend professional help"}
        ]
        
        # Age-specific rules
        self.age_rules = [
            {"context": "young_child", "age_max": 7, "rule": "Use shorter questions, simple words, single concrete issues"},
            {"context": "school_age", "age_min": 7, "age_max": 12, "rule": "Balance directness with sensitivity, offer choices"},
            {"context": "adolescent", "age_min": 13, "rule": "Respect autonomy, be honest about confidentiality limits"}
        ]
        
        # Symptom mapping
        self.symptom_keywords = {
            "withdrawn": {"conditions": ["Depression", "Anxiety", "Autism"], "severity": "moderate"},
            "irritability": {"conditions": ["Depression", "ADHD", "Anxiety"], "severity": "moderate"},
            "racing heart": {"conditions": ["Anxiety", "Panic Disorder"], "severity": "high"},
            "suicide": {"conditions": ["Depression", "Crisis"], "severity": "critical"},
            "hurt myself": {"conditions": ["Self-harm", "Crisis"], "severity": "critical"},
            "bullying": {"conditions": ["Trauma", "Anxiety"], "severity": "moderate"}
        }
        
        # Escalation triggers
        self.escalation_triggers = [
            {"name": "chronic_concern", "criteria": "withdrawn OR irritable AND duration > 2 weeks", "action": "Recommend professional consultation"},
            {"name": "acute_crisis", "criteria": "suicide OR self-harm", "action": "IMMEDIATE safety protocol"},
            {"name": "academic_decline", "criteria": "school difficulties persist", "action": "Consult school counselor"}
        ]
        
        # Conversational prompts
        self.conversation_prompts = [
            {"intent": "general_stress", "prompt": "What's your favorite way to relax or de-stress?"},
            {"intent": "social_connection", "prompt": "How are things going with your friends?"},
            {"intent": "mental_load", "prompt": "What has been taking up most of your mental energy these days?"},
            {"intent": "future_outlook", "prompt": "What's something exciting you're looking forward to?"}
        ]

class ConversationManager:
    def __init__(self):
        self.sessions = {}
        self.knowledge_base = MentalHealthKnowledgeBase()
    
    def get_session(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'history': [],
                'start_time': datetime.now(),
                'topics_discussed': set(),
                'concerns_detected': [],
                'risk_level': 'low'
            }
        return self.sessions[session_id]
    
    def analyze_message(self, message: str, age: Optional[int] = None) -> Tuple[str, List[str], bool]:
        """Analyze message and generate appropriate response"""
        message_lower = message.lower()
        
        # Safety check first
        safety_concerns = self._check_safety_concerns(message_lower)
        if safety_concerns:
            return self._get_safety_response(), safety_concerns, True
        
        # Detect intent and generate response
        response = self._generate_contextual_response(message_lower, age)
        concerns = self._detect_concerns(message_lower)
        
        return response, concerns, False
    
    def _check_safety_concerns(self, message: str) -> List[str]:
        """Check for immediate safety concerns"""
        concerns = []
        critical_keywords = ['kill myself', 'suicide', 'hurt myself', 'want to die', 'end it all']
        
        for keyword in critical_keywords:
            if keyword in message:
                concerns.append('critical_safety_alert')
                break
        
        high_concern_keywords = ['abuse', 'hit me', 'scared at home', 'bully', 'tease me']
        for keyword in high_concern_keywords:
            if keyword in message:
                concerns.append('high_concern')
                break
                
        return concerns
    
    def _get_safety_response(self) -> str:
        """Get safety protocol response"""
        return "I'm really concerned about what you're sharing. It's important to talk to a trusted adult about this right away. Please tell your parent, teacher, or call a helpline like Kids Helpline (1-800-668-6868)."
    
    def _generate_contextual_response(self, message: str, age: Optional[int]) -> str:
        """Generate age-appropriate, context-aware response"""
        
        # Match patterns from QA pairs
        for qa in self.knowledge_base.qa_pairs:
            if 'user_says' in qa and qa['user_says'].lower() in message:
                return qa['agent_response']
        
        # Age-appropriate responses
        if age and age < 7:
            return self._get_young_child_response(message)
        elif age and age >= 13:
            return self._get_adolescent_response(message)
        else:
            return self._get_general_response(message)
    
    def _get_young_child_response(self, message: str) -> str:
        """Responses for young children (under 7)"""
        simple_responses = [
            "Can you tell me more about that?",
            "How does that make you feel?",
            "What's something that makes you happy?",
            "Do you want to talk about your friends or school?"
        ]
        import random
        return random.choice(simple_responses)
    
    def _get_adolescent_response(self, message: str) -> str:
        """Responses for adolescents (13+)"""
        adolescent_responses = [
            "I appreciate you sharing that. What's been on your mind lately?",
            "That sounds challenging. How long have you been feeling this way?",
            "What do you think would help with this situation?",
            "Is there someone you feel comfortable talking to about this?"
        ]
        import random
        return random.choice(adolescent_responses)
    
    def _get_general_response(self, message: str) -> str:
        """General responses for school-age children"""
        general_responses = [
            "Thanks for telling me that. Can you say more about how you're feeling?",
            "I understand. What's been the hardest part about this?",
            "That sounds tough. What usually helps you feel better?",
            "How are things going with your friends and family?"
        ]
        import random
        return random.choice(general_responses)
    
    def _detect_concerns(self, message: str) -> List[str]:
        """Detect potential mental health concerns"""
        concerns = []
        
        for keyword, info in self.knowledge_base.symptom_keywords.items():
            if keyword in message:
                concerns.append(f"potential_{info['conditions'][0].lower()}")
        
        return concerns
    
    def apply_ethical_filters(self, response: str) -> str:
        """Apply ethical guardrails to response"""
        for guardrail in self.knowledge_base.ethical_guardrails:
            if guardrail['avoid_pattern'] in response.lower():
                response = response.replace(
                    guardrail['avoid_pattern'], 
                    guardrail['best_practice']
                )
        return response

# Initialize conversation manager
conversation_manager = ConversationManager()

@mental_health_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Mental Health Agent started: {mental_health_agent.name}")
    ctx.logger.info(f"Agent address: {mental_health_agent.address}")

@mental_health_agent.on_message(model=ChildMessage)
async def handle_child_message(ctx: Context, sender: str, msg: ChildMessage):
    ctx.logger.info(f"Received message from {sender}: {msg.message}")
    
    # Analyze message and generate response
    response, concerns, safety_alert = conversation_manager.analyze_message(
        msg.message, msg.age
    )
    
    # Apply ethical filters
    response = conversation_manager.apply_ethical_filters(response)
    
    # Update session
    session = conversation_manager.get_session(msg.session_id)
    session['history'].append({
        'user': msg.message,
        'agent': response,
        'timestamp': datetime.now().isoformat()
    })
    session['concerns_detected'].extend(concerns)
    
    # Send response
    await ctx.send(sender, AgentResponse(
        response=response,
        concerns_detected=concerns,
        safety_alert=safety_alert,
        follow_up_needed=len(concerns) > 0,
        session_id=msg.session_id
    ))

@mental_health_agent.on_query(model=ConversationAnalysis, replies=ConversationAnalysis)
async def handle_analysis_query(ctx: Context, sender: str, query: ConversationAnalysis):
    """Provide conversation analysis for caregivers"""
    if query.session_id in conversation_manager.sessions:
        session = conversation_manager.sessions[query.session_id]
        
        # Determine risk level
        risk_level = "low"
        if any('critical' in concern for concern in session['concerns_detected']):
            risk_level = "critical"
        elif session['concerns_detected']:
            risk_level = "moderate"
        
        recommendations = []
        if risk_level == "critical":
            recommendations = ["IMMEDIATE: Contact emergency services or crisis helpline"]
        elif risk_level == "moderate":
            recommendations = [
                "Consult with school counselor or pediatrician",
                "Monitor changes in behavior and mood",
                "Maintain open communication with child"
            ]
        else:
            recommendations = ["Continue supportive conversations", "Monitor overall well-being"]
        
        await ctx.send(sender, ConversationAnalysis(
            session_id=query.session_id,
            risk_level=risk_level,
            topics_discussed=list(session['topics_discussed']),
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        ))

if __name__ == "__main__":
    mental_health_agent.run()