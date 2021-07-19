import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { IndexInfoModalComponent } from './index-info-modal.component';

describe('IndexInfoModalComponent', () => {
  let component: IndexInfoModalComponent;
  let fixture: ComponentFixture<IndexInfoModalComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ IndexInfoModalComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(IndexInfoModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
