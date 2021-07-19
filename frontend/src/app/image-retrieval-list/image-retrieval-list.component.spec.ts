import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ImageRetrievalListComponent } from './image-retrieval-list.component';

describe('ImageRetrievalListComponent', () => {
  let component: ImageRetrievalListComponent;
  let fixture: ComponentFixture<ImageRetrievalListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ImageRetrievalListComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ImageRetrievalListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
